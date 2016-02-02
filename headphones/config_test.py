#import unittest
#import mock
from unittest import TestCase
from mock import Mock, MagicMock

import configobj

from headphones.config import path

class ConfigPathTest(TestCase):
    def test_path(self):
        p = path('/tmp')
        print path
        self.assertIsInstance(p, path)
        self.assertIsNotNone(p)

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
        self.assertIn('headphones.config.path', p1.__repr__() )


import headphones.config

# patch required, since Config works ower a
@mock.patch('headphones.config.ConfigObj', name='ConfigObjMock')
class ConfigTest(TestCase):

    def putConfigToFabric(self, config_obj_fabric_mock):
        """ Helper for setting up the config_obj_fabric"""

        config_obj_mock = MagicMock( )
        config_obj_fabric_mock.return_value = config_obj_mock
        return config_obj_mock

    def test_create(self, config_obj_fabric_mock):
        """Test creating headphones.Config"""

        cf = headphones.config.Config('/tmp/notexist')
        self.assertIsInstance(cf, headphones.config.Config)

    def test_write(self, config_obj_fabric_mock):
        """ Test writing config """
        path = '/tmp/notexist'

        conf_mock = self.putConfigToFabric(config_obj_fabric_mock)

        # call methods
        cf = headphones.config.Config(path)
        cf.write()

        # assertions

        self.assertTrue(conf_mock.write.called)
        self.assertEqual(conf_mock.filename, path)

        general_opts_set = conf_mock['General'].__setitem__.call_args_list
        general_opts_set = map( lambda x : x[0][0], general_opts_set )
        self.assertIn('download_dir', general_opts_set , 'There is no download_dir in ConfigObj (submodule of Config)')

