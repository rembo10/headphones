from unittestcompat import TestCase, TestArgs
from _viewmodel import OptionBase, OptionInternal, OptionDeprecated

from _viewmodel import CssClassable


class CssClassableTest(TestCase):

    @TestArgs(
        (None, []),

        ("class-red", ['class-red']),

        (["class-red"], ['class-red']),
        (['class-red', 'green'], ['class-red', 'green']),

        (tuple(["-red"]), ['-red']),
        (tuple(['-box', '-shad']), ['-box', '-shad']),
    )
    def test_cssclasses_setget(self, val, exp):
        """ CssClassable cssclasses set-get normal """

        o = CssClassable()
        o.cssclasses = val

        self.assertEqual(o.cssclasses, exp)

    @TestArgs(
        (True),
        (1),
    )
    def test_cssclasses_set_raises(self, val):
        """ CssClassable cssclasses set SHOULD raise on invalid values """

        o = CssClassable()
        with self.assertRaisesRegexp(TypeError, r'Unexpected\s+type.*"cssclasses'):
            o.cssclasses = val
        self.assertEqual(o.cssclasses, [])

    @TestArgs(
        (None, ''),

        ("class-red", 'class-red'),

        (["class-red"], 'class-red'),
        (['class-red', 'green'], 'class-red green'),

        (tuple(["-red"]), '-red'),
        (tuple(['-box', '-shad']), '-box -shad'),
    )
    def test_uiCssClasses(self, val, exp):
        o = CssClassable()
        o.cssclasses = val

        self.assertEqual(o.uiCssClasses(), exp)


class OptionInternalTest(TestCase):

    # ---------------------------------------------------------------
    # __init__
    # ---------------------------------------------------------------
    def test_init(self):
        """ OptionInternal: __init__ """
        p = OptionInternal('KEY', 'GeneralSection', 0, initype=int)

        self.assertIsNotNone(p)
        self.assertIsInstance(p, OptionBase)
        self.assertIsInstance(p, OptionInternal)

    # ---------------------------------------------------------------
    # render
    # ---------------------------------------------------------------
    def test_render(self):
        """ OptionInternal: render """
        p = OptionInternal('KEY', 'GeneralSection', 0, initype=int)

        self.assertEqual(p.render(), "")


class OptionDeprecatedTest(TestCase):

    # ---------------------------------------------------------------
    # __init__
    # ---------------------------------------------------------------
    def test_init(self):
        """ OptionDeprecated: __init__ """
        p = OptionDeprecated('KEY', 'GeneralSection', 0, initype=int)

        self.assertIsNotNone(p)
        self.assertIsInstance(p, OptionBase)
        self.assertIsInstance(p, OptionDeprecated)

    # ---------------------------------------------------------------
    # render
    # ---------------------------------------------------------------
    def test_render(self):
        """ OptionDeprecated: render """
        p = OptionDeprecated('KEY', 'GeneralSection', 0, initype=int)

        self.assertEqual(p.render(), "")
