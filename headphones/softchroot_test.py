import os
import mock
from headphones.unittestcompat import TestCase, TestArgs

from headphones.softchroot import SoftChroot
from headphones.exceptions import SoftChrootError


class SoftChrootTest(TestCase):
    def test_create(self):
        """ create headphones.SoftChroot """

        cf = SoftChroot('/tmp/')
        self.assertIsInstance(cf, SoftChroot)
        self.assertTrue(cf.isEnabled())
        self.assertEqual(cf.getRoot(), '/tmp/')

    @TestArgs(
        (None),
        (''),
        ('      '),
    )
    def test_create_disabled(self, empty_path):
        """ create DISABLED SoftChroot """

        cf = SoftChroot(empty_path)
        self.assertIsInstance(cf, SoftChroot)
        self.assertFalse(cf.isEnabled())
        self.assertIsNone(cf.getRoot())

    def test_create_on_not_exists_dir(self):
        """ create SoftChroot on non existent dir """

        path = os.path.join('/tmp', 'notexist', 'asdf', '11', '12', 'np', 'itsssss')

        cf = None
        with self.assertRaises(SoftChrootError) as exc:
            cf = SoftChroot(path)
        self.assertIsNone(cf)

        self.assertRegexpMatches(str(exc.exception), r'No such directory')
        self.assertRegexpMatches(str(exc.exception), path)

    @mock.patch('headphones.softchroot.os', wrap=os, name='OsMock')
    def test_create_on_file(self, os_mock):
        """ create SoftChroot on file, not a directory """

        path = os.path.join('/tmp', 'notexist', 'asdf', '11', '12', 'np', 'itsssss')

        os_mock.path.sep = os.path.sep
        os_mock.path.isdir.side_effect = lambda x: x != path

        cf = None
        with self.assertRaises(SoftChrootError) as exc:
            cf = SoftChroot(path)
        self.assertIsNone(cf)

        self.assertTrue(os_mock.path.isdir.called)

        self.assertRegexpMatches(str(exc.exception), r'No such directory')
        self.assertRegexpMatches(str(exc.exception), path)

    @TestArgs(
        (None, None),
        ('', ''),
        ('      ', '      '),
        ('/tmp/', '/'),
        ('/tmp/asdf', '/asdf'),
    )
    def test_apply(self, p, e):
        """ apply SoftChroot """
        sc = SoftChroot('/tmp/')
        a = sc.apply(p)
        self.assertEqual(a, e)

    @TestArgs(
        ('/'),
        ('/nonch/path/asdf'),
        ('tmp/asdf'),
    )
    def test_apply_out_of_root(self, p):
        """ apply SoftChroot to paths outside of the chroot """
        sc = SoftChroot('/tmp/')
        a = sc.apply(p)
        self.assertEqual(a, '/')

    @TestArgs(
        (None, None),
        ('', ''),
        ('      ', '      '),
        ('/', '/tmp/'),
        ('/asdf', '/tmp/asdf'),
        ('/asdf/', '/tmp/asdf/'),
        ('localdir/adf', '/tmp/localdir/adf'),
        ('localdir/adf/', '/tmp/localdir/adf/'),
    )
    def test_revoke(self, p, e):
        """ revoke SoftChroot """
        sc = SoftChroot('/tmp/')
        a = sc.revoke(p)
        self.assertEqual(a, e)

    @TestArgs(
        (None),
        (''),
        ('     '),
        ('/tmp'),
        ('/tmp/'),
        ('/tmp/asdf'),
        ('/tmp/localdir/adf'),
        ('localdir/adf'),
        ('localdir/adf/'),
    )
    def test_actions_on_disabled(self, p):
        """ disabled SoftChroot should not change args on apply and revoke """
        sc = SoftChroot(None)
        a = sc.apply(p)
        self.assertEqual(a, p)

        r = sc.revoke(p)
        self.assertEqual(r, p)
