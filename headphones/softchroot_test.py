import os
import mock
from unittestcompat import TestCase, TestArgs

from headphones.softchroot import SoftChroot
from headphones.exceptions import SoftChrootError


class SoftChrootTest(TestCase):

    #
    # INIT TESTS
    #

    @TestArgs(
        ('/tmp', '/tmp/'),
        ('/tmp/', '/tmp/'),
    )
    def test_init_enabled(self, rt, exp_chroot):
        """ softchroot: test_init_enabled """
        sc = SoftChroot(rt)

        enabled = sc.isEnabled()
        path = sc.getRoot()
        self.assertIsInstance(sc, SoftChroot)
        self.assertTrue(enabled)
        self.assertEqual(exp_chroot, path)

    @TestArgs(
        (None),
        (''),
        ('     '),
    )
    def test_init_disabled(self, rt):
        """ softchroot: test_init_disabled """
        sc = SoftChroot(rt)

        enabled = sc.isEnabled()
        path = sc.getRoot()
        self.assertIsInstance(sc, SoftChroot)
        self.assertFalse(enabled)
        self.assertIsNone(path)

    def test_create_on_not_exists_dir(self):
        """ softchroot: init on non existent dir SHOULD RAISE """

        path = os.path.join('/tmp', 'notexist', 'asdf', '11', '12', 'np', 'itsssss')

        cf = None
        with self.assertRaises(SoftChrootError) as exc:
            cf = SoftChroot(path)
        self.assertIsNone(cf)

        self.assertRegexpMatches(str(exc.exception), r'No such directory')
        self.assertRegexpMatches(str(exc.exception), path)

    @mock.patch('headphones.softchroot.os', wrap=os, name='OsMock')
    def test_create_on_file(self, os_mock):
        """ softchroot: init on file, not a directory SHOULD RAISE """

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

    # ==========================================
    # APPLY
    #

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
        """ softchroot: disabled SC, apply and revoke should not change args """
        sc = SoftChroot(None)
        a = sc.apply(p)
        self.assertEqual(a, p)

        r = sc.revoke(p)
        self.assertEqual(r, p)

    @TestArgs(
        (None, None),
        ('', ''),
        ('      ', '      '),
    )
    def test_apply_to_empty(self, p, e):
        """ softchroot: apply to empty """
        sc = SoftChroot('/tmp/')
        a = sc.apply(p)
        self.assertEqual(a, e)

    @TestArgs(
        ('/tmp/', '/'),
        ('/tmp/asdf', '/asdf'),
    )
    def test_apply(self, p, e):
        """ softchroot: apply """
        sc = SoftChroot('/tmp/')
        a = sc.apply(p)
        self.assertEqual(a, e)

    @TestArgs(
        ('/', '/'),
        ('/nonch/path/asdf', '/nonch/path/asdf'),
        ('tmp/asdf', '/tmp/asdf'),
    )
    def test_apply_out_of_root(self, p, e):
        """ softchroot: apply to paths outside of the chroot """
        chroot = '/tmp/'
        sc = SoftChroot(chroot)
        a = sc.apply(p)

        # !!! Important thing for compatibility with non-soft-chroot:
        # !!! the path outside of chroot should be the same, but with chroot prefix!!
        self.assertEqual(a, e)

    @TestArgs(
        ('/tmp', '/tmp', '/'),
        ('/tmp/', '/tmp', '/'),
    )
    def test_apply_to_chroot_without_slash(self, chroot_root, path, exp):
        """ softchroot: apply to the chroot path without trailing slash """
        sc = SoftChroot(chroot_root)
        a = sc.apply(path)
        self.assertEqual(a, exp)

    # ==========================================
    # REVOKE
    #
    @TestArgs(
        (None, '/tmp/'),
        ('', '/tmp/'),
        ('      ', '/tmp/'),
    )
    def test_revoke_empty(self, p, e):
        """ softchroot: revoke on empty """
        sc = SoftChroot('/tmp/')
        a = sc.revoke(p)
        self.assertEqual(a, e)

    @TestArgs(
        ('/', '/tmp/'),
        ('/asdf', '/tmp/asdf'),
        ('/asdf/', '/tmp/asdf/'),
        ('localdir/adf', '/tmp/localdir/adf'),
        ('localdir/adf/', '/tmp/localdir/adf/'),
    )
    def test_revoke(self, p, e):
        """ softchroot: revoke """
        sc = SoftChroot('/tmp/')
        a = sc.revoke(p)
        self.assertEqual(a, e)
