import os
import mock
from headphones.unittestcompat import TestCase
#from mock import MagicMock

from headphones.softchroot import SoftChroot
from headphones.exceptions import SoftChrootError

class SoftChrootTest(TestCase):
    def test_create(self):
        """ create headphones.SoftChroot """

        cf = SoftChroot('/tmp/')
        self.assertIsInstance(cf, SoftChroot)

    def test_create_on_not_exists_dir(self):
        """ create SoftChroot on non existent dir """

        path = os.path.join('/tmp', 'notexist', 'asdf', '11', '12', 'np', 'itsssss')

        with self.assertRaises(SoftChrootError) as exc:
            cf = SoftChroot(path)

        self.assertRegexpMatches(str(exc.exception), r'No such directory')
        self.assertRegexpMatches(str(exc.exception), path)

    @mock.patch('headphones.softchroot.os', wrap=os, name='OsMock')
    def test_create_on_file(self, os_mock):
        """ create SoftChroot on file, not a directory """

        path = os.path.join('/tmp', 'notexist', 'asdf', '11', '12', 'np', 'itsssss')

        os_mock.path.sep = os.path.sep
        os_mock.path.isdir.side_effect = lambda x: x != path

        with self.assertRaises(SoftChrootError) as exc:
            cf = SoftChroot(str(path))

        self.assertTrue(os_mock.path.isdir.called)

        self.assertRegexpMatches(str(exc.exception), r'No such directory')
        self.assertRegexpMatches(str(exc.exception), path)
