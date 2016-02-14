#import unittest
import mock
from headphones.unittestcompat import TestCase, TestArgs
from mock import MagicMock

import headphones.config
from headphones.config import path
import re


class ConfigPathTest(TestCase):

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
        self.assertIn('headphones.config.path', p1.__repr__())

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


class ConfigApiTest(TestCase):
    """ Common tests for headphones.Config

    Common tests for headphones.Config This test suite guarantees, that external
    API of the Config class conforms all expectations of other modules.
    """

    def _setUpConfigMock(self, mock, sections):
        # every constructor `xx = ConfigObj()` in headphones.config will return
        # this mock:
        self.config_mock = self.config_module_mock.return_value = mock
 
        if sections:
            mock.__contains__.side_effect = sections.__contains__
            mock.__getitem__.side_effect = sections.__getitem__
            mock.__setitem__.side_effect = sections.__setitem__
            mock.items.side_effect = sections.items

        return mock

    def setUp(self):
        # patch for low-level ConfigObj for entire test class
        # result - each test_* method will get one additional
        # argument during testing
        self.config_module_mock_patcher = mock.patch('headphones.config.ConfigObj', name='ConfigObjModuleMock')
        self.config_module_mock = self.config_module_mock_patcher.start()

        existing_sections = {'General': {}, 'Email': {}}
        # every constructor `xx = ConfigObj()` in headphones.config will return
        # this mock:
        self._setUpConfigMock(MagicMock(), existing_sections)

    def tearDown(self):
        self.config_module_mock_patcher.stop()

    def test_constructor(self):
        """ Config : creating """

        cf = headphones.config.Config('/tmp/notexist')
        self.assertIsInstance(cf, headphones.config.Config)

    @TestArgs(
        # this sections are explicitly added in the test body:
        ('General', False),
        ('Email', False),

        # this sections will not be created nor in the test, either in the
        # Config module
        ('some_new_section_never_defined', True),
        ('another_new_section_never_defined', True),
    )
    def test_check_section(self, section_name, expected_return):
        """ Config : check_section """
        path = '/tmp/notexist'

        # call methods
        c = headphones.config.Config(path)
        res = c.check_section(section_name)
        res2 = c.check_section(section_name)

        # assertions:
        self.assertEqual(res, expected_return)
        self.assertFalse(res2)

    @TestArgs(
        ('api_enabled', 0, int),
        ('Api_Key', '', str),
    )
    def test_check_setting(self, setting_name, expected_return, expected_instance):
        """ Config: check_setting , basic cases """
        path = '/tmp/notexist'

        # call methods
        c = headphones.config.Config(path)
        res = c.check_setting(setting_name)
        res2 = c.check_setting(setting_name)

        # assertions:
        self.assertIsInstance(res, expected_instance)
        self.assertEqual(res, expected_return)
        self.assertEqual(res, res2)

    @TestArgs(
        (''),
        ('This_IsNew_Name'),
    )
    def test_check_setting_raise_on_unknown_settings(self, setting_name):
        """ Config: check_setting should raise on unknown """
        path = '/tmp/notexist'

        exc_regex = re.compile(setting_name, re.IGNORECASE)

        # call methods
        c = headphones.config.Config(path)
        # assertions:
        with self.assertRaisesRegexp(KeyError, exc_regex) as exc:
            res = c.check_setting(setting_name)
        pass

    @TestArgs(
        (None)
    )
    def test_check_setting_raise_on_none(self, setting_name):
        """ Config: check_setting shoud raise on None name """
        path = '/tmp/notexist'

        # call methods
        c = headphones.config.Config(path)
        # assertions:
        with self.assertRaises(AttributeError) as exc:
            res = c.check_setting(setting_name)
        pass

    def test_write(self):
        """ Config : write """
        path = '/tmp/notexist'

        # overload mocks, defined in setUp:
        old_conf_mock = self._setUpConfigMock(MagicMock(), {'a' : {}})

        option_name_not_from_definitions = 'some_invalid_option_with_super_uniq1_name'
        option_name_not_from_definitions_value = 1
        old_conf_mock['asdf'] = { option_name_not_from_definitions : option_name_not_from_definitions_value }


        # call methods
        cf = headphones.config.Config(path)

        # overload mock-patching for NEW CONFIG
        new_patcher = mock.patch('headphones.config.ConfigObj', name='NEW_ConfigObjModuleMock_FOR_WRITE')
        
        new_conf_module_mock = new_patcher.start()
        new_conf_mock = \
            new_conf_module_mock.return_value = \
            MagicMock()
        cf.write()
        new_patcher.stop()

        # assertions:
        self.assertFalse(old_conf_mock.write.called, 'write not called for old config')
        self.assertTrue(new_conf_mock.write.called, 'write called for new config')
        self.assertEqual(new_conf_mock.filename, path)

        new_conf_mock['General'].__setitem__.assert_any_call('download_dir', '')
        # from 3.5... new_conf_mock['asdf'].__setitem__.assert_not_called('download_dir', '')
        new_conf_mock['asdf'].__setitem__.assert_any_call(option_name_not_from_definitions, option_name_not_from_definitions_value)

    @TestArgs(
        ('', []),
        ('ABCDEF', [('A', 'B', 'C'), ('D', 'E', 'F')]),
        (['ABC', 'DEF'], []),
        ([1], []),
        ([1, 2], []),
        ([1, 2, 3], [(1, 2, 3)]),

        ([1, 2, 3, 'Aaa'], [(1, 2, 3)]),
        ([1, 2, 3, 'Aaa', 'Bbba'], [(1, 2, 3)]),
        ([1, 2, 3, 'Aaa', 'Bbba', 'Ccccc'], [(1, 2, 3), ('Aaa', 'Bbba', 'Ccccc')]),
    )
    def test_get_extra_newznabs(self, conf_value, expected):
        """ Config: get_extra_newznabs """
        path = '/tmp/notexist'

        #itertools.izip(*[itertools.islice('', i, None, 3) for i in range(3)])
        # set up mocks:
        # 'EXTRA_NEWZNABS': (list, 'Newznab', ''),
        # 'EXTRA_TORZNABS': (list, 'Torznab', ''),
        self.config_mock["Newznab"] = {"extra_newznabs": conf_value}

        # call methods
        c = headphones.config.Config(path)
        res = c.get_extra_newznabs()

        # assertions:
        self.assertEqual(res, expected)

    def test_clear_extra_newznabs(self):
        """ Config: clear_extra_newznabs """
        path = '/tmp/notexist'

        random_value = 1827746
        self.config_mock["Newznab"] = {"extra_newznabs": [1, 2, 3]}
        self.config_mock["Newznab"] = {"do_not_touch": random_value}

        # call methods
        c = headphones.config.Config(path)
        res = c.clear_extra_newznabs()

        # assertions:
        self.assertEqual(self.config_mock["Newznab"]["extra_newznabs"], [])
        self.assertEqual(self.config_mock["Newznab"]["do_not_touch"], random_value)

    @TestArgs(
        ('', []),
        ('ABCDEF', [('A', 'B', 'C'), ('D', 'E', 'F')]),
        (['ABC', 'DEF'], []),
        ([1], []),
        ([1, 2], []),
        ([1, 2, 3], [(1, 2, 3)]),

        ([1, 2, 3, 'Aaa'], [(1, 2, 3)]),
        ([1, 2, 3, 'Aaa', 'Bbba'], [(1, 2, 3)]),
        ([1, 2, 3, 'Aaa', 'Bbba', 'Ccccc'], [(1, 2, 3), ('Aaa', 'Bbba', 'Ccccc')]),
    )
    def add_extra_newznab(self, value, expected):
        """ Config: add_extra_newznab """
        path = '/tmp/notexist'

        self.config_mock["Newznab"] = {"extra_newznabs": conf_value}

        # call methods
        c = headphones.config.Config(path)
        res = c.add_extra_newznab(value)

        # assertions:
        self.assertEqual(res, expected)

    @TestArgs(
        ('', []),
        ('ABCDEF', [('A', 'B', 'C'), ('D', 'E', 'F')]),
        (['ABC', 'DEF'], []),
        ([1], []),
        ([1, 2], []),
        ([1, 2, 3], [(1, 2, 3)]),

        ([1, 2, 3, 'Aaa'], [(1, 2, 3)]),
        ([1, 2, 3, 'Aaa', 'Bbba'], [(1, 2, 3)]),
        ([1, 2, 3, 'Aaa', 'Bbba', 'Ccccc'], [(1, 2, 3), ('Aaa', 'Bbba', 'Ccccc')]),
    )
    def add_extra_newznab(self, conf_value, expected):
        """
get_extra_torznabs(self)
clear_extra_torznabs(self)
add_extra_torznab(self, torznab)
__getattr__(self, name)
__setattr__(self, name, value)
process_kwargs(self, kwargs)
"""

        """ Config: get_extra_newznabs """
        path = '/tmp/notexist'

        #itertools.izip(*[itertools.islice('', i, None, 3) for i in range(3)])
        # set up mocks:
        # 'EXTRA_NEWZNABS': (list, 'Newznab', ''),
        # 'EXTRA_TORZNABS': (list, 'Torznab', ''),
        self.config_mock["Newznab"] = {"extra_newznabs": conf_value}

        # call methods
        c = headphones.config.Config(path)
        res = c.get_extra_newznabs()

        # assertions:
        self.assertEqual(res, expected)
