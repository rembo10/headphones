import os
import mock
from headphones.unittestcompat import TestCase
from mock import MagicMock

from headphones.softchroot import SoftChroot
from headphones.exceptions import SoftChrootError

class SoftChrootTest(TestCase):
    def test_create(self):
        """ create headphones.SoftChroot """

        cf = SoftChroot('/tmp/')
        self.assertIsInstance(cf, SoftChroot)

    @mock.patch('headphones.config.ConfigObj', name='ConfigObjMock')
    def test_create_on_file(self, config_obj_fabric_mock):
        """ create SoftChroot on file, not a directory """

        path = os.path.join('tmp', 'notexist', 'asdf', '11', '12', 'np', 'itsssss')

        with self.assertRaises(SoftChrootError) as exc:
            cf = SoftChroot(path)

        self.assertRegexpMatches(str(exc.exception), r'No such directory')
        self.assertRegexpMatches(str(exc.exception), path)

    @mock.patch('headphones.softchroot', name='SoftChrootMock')
    def test_create_on_file(self, config_obj_fabric_mock):
        """ create SoftChroot on file, not a directory """

        path = os.path.join('tmp', 'notexist', 'asdf', '11', '12', 'np', 'itsssss')

        with self.assertRaises(SoftChrootError) as exc:
            cf = SoftChroot(path)

        self.assertRegexpMatches(str(exc.exception), r'No such directory')
        self.assertRegexpMatches(str(exc.exception), path)
