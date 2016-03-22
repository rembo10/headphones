from unittestcompat import TestCase, TestArgs

from typeconv import path, boolext
from typeconv import floatnullable
from typeconv import intnullable


class PathTest(TestCase):

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
        self.assertIn('headphones.config.types.path', p1.__repr__())

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


class boolextTest(TestCase):

    @TestArgs(
        (1),
        (2),
        ([1, 2]),
        (True),
        ('Y'),
        ('true'),
        ('on'),
        ('t'),
        ('+'),
        ('1'),
        ('YES'),
    )
    def test_true(self, val):
        act = boolext(val)
        self.assertTrue(act)

    @TestArgs(
        (None),
        (False),
        ([]),
        (0),
        (''),
        ('nO'),
        ('no'),
        ('n'),
        ('fAlse'),
        ('-'),
        ('off'),
    )
    def test_false(self, val):
        act = boolext(val)
        self.assertFalse(act)


class floatnullableTest(TestCase):

    @TestArgs(
        (1, 1.0),
        (2, 2.0),
        ("1", 1.0),
        ("3.14", 3.14),
        (0, 0.0),
        (-1, -1.0),
        ("-300.12", -300.12),
        (123.456, 123.456),
        (-0.06, -0.06),
    )
    def test_floatnullable(self, raw, exp):
        act = floatnullable(raw)
        self.assertEqual(act, exp)

    @TestArgs(
        (None),
        (''),
        (u''),
        ('   '),
        (u' '),
        ("""
"""),
        (u'                '),
    )
    def test_floatnullable_to_none(self, raw):
        act = floatnullable(raw)
        self.assertIsNone(act)

    @TestArgs(
        ([1, 2, 3]),
        ('asdf'),
    )
    def test_floatnullable_raises(self, raw):
        with self.assertRaises(Exception):
            floatnullable(raw)


class intnullableTest(TestCase):

    @TestArgs(
        (1, 1),
        (2, 2),
        ("1", 1),
        (0, 0),
        (-1, -1),
        (123.456, 123),
        (-0.06, 0),
    )
    def test_intnullable(self, raw, exp):
        act = intnullable(raw)
        self.assertEqual(act, exp)

    @TestArgs(
        (None),
        (''),
        (u''),
        ('   '),
        (u' '),
        ("""
"""),
        (u'                '),
    )
    def test_intnullable_to_none(self, raw):
        act = intnullable(raw)
        self.assertIsNone(act)

    @TestArgs(
        ([1, 2, 3]),
        ('asdf'),
        ("3.14"),
        ("-300.12"),
    )
    def test_intnullable_raises(self, raw):
        with self.assertRaises(Exception):
            intnullable(raw)
