from unittestcompat import TestCase, TestArgs

from headphones.config.typeconv import path, boolext

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
