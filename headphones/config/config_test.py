import sys
import mock
from mock import MagicMock
import re
import unittestcompat
from unittestcompat import TestCase, TestArgs

import headphones.config

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

    def test_write(self):
        """ Config : write """
        path = '/tmp/notexist'

        # overload mocks, defined in setUp:
        old_conf_mock = self._setUpConfigMock(MagicMock(), {'a': {}})

        option_name_not_from_definitions = 'some_invalid_option_with_super_uniq1_name'
        option_name_not_from_definitions_value = 1
        old_conf_mock['asdf'] = {option_name_not_from_definitions: option_name_not_from_definitions_value}

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

        # IMPORTANT ASSERTS: they check, that options are passed to the low-level ConfigObj
        # with appropriate values and names
        new_conf_mock['General'].__setitem__.assert_any_call('download_dir', '')
        new_conf_mock['Email'].__setitem__.assert_any_call('email_enabled', 0)
        new_conf_mock['Email'].__setitem__.assert_any_call('email_from', '')
        # from 3.5... new_conf_mock['asdf'].__setitem__.assert_not_called('download_dir', '')
        new_conf_mock['asdf'].__setitem__.assert_any_call(option_name_not_from_definitions,
                                                          option_name_not_from_definitions_value)

    @unittestcompat.skip("process_kwargs should be removed")
    def test_process_kwargs(self):
        self.assertTrue(True)

    # ===========================================================
    #   GET ATTR
    # ===========================================================

    @TestArgs(
        ('ADD_ALBUM_ART', True),
        ('ALBUM_ART_FORMAT', 'shmolder'),
        ('API_ENABLED', 1),
        ('API_KEY', 'Hello'),
    )
    def test__getattr__ConfValues(self, name, value):
        """ Config: __getattr__ with setting value explicit """
        path = '/tmp/notexist'

        self.config_mock["General"] = {name.lower(): value}

        # call methods
        c = headphones.config.Config(path)
        act = c.__getattr__(name)

        # assertions:
        self.assertEqual(act, value)

    @TestArgs(
        ('ADD_ALBUM_ART', 0),
        ('ALBUM_ART_FORMAT', 'folder'),
        ('API_ENABLED', 0),
        ('API_KEY', ''),
    )
    def test__getattr__ConfValuesDefault(self, name, value):
        """ Config: __getattr__ from config(by braces), default values """
        path = '/tmp/notexist'

        # call methods
        c = headphones.config.Config(path)
        res = c.__getattr__(name)

        # assertions:
        self.assertEqual(res, value)

    def test__getattr__ConfValuesDefaultUsingDotNotation(self):
        """ Config: __getattr__ from config (by dot), default values """
        path = '/tmp/notexist'

        # call methods
        c = headphones.config.Config(path)

        # assertions:
        self.assertEqual(c.ALBUM_ART_FORMAT, 'folder')
        self.assertEqual(c.API_ENABLED, 0)
        self.assertEqual(c.API_KEY, '')

    def test__getattr__OwnAttributes(self):
        """ Config: __getattr__ access own attrs """
        path = '/tmp/notexist'

        # call methods
        c = headphones.config.Config(path)

        # assertions:
        self.assertIsNotNone(c)
        self.assertIn('<headphones.config.Config', c.__str__())

    # ===========================================================
    #   SET ATTR
    # ===========================================================

    @TestArgs(
        ('ADD_ALBUM_ART', True),
        ('ALBUM_ART_FORMAT', 'shmolder'),
        ('API_ENABLED', 1),
        ('API_KEY', 'Hello'),
    )
    def test__setattr__ConfValuesDefault(self, name, value):
        """ Config: __setattr__ with setting value explicit """
        path = '/tmp/notexist'

        # call methods
        c = headphones.config.Config(path)
        act = c.__setattr__(name, value)

        # assertions:
        self.assertEqual(self.config_mock["General"][name.lower()], value)
        self.assertEqual(act, value)

    def test__setattr__ExplicitSetUsingDotNotation(self):
        """ Config: __setattr__ with setting values using dot notation """
        path = '/tmp/notexist'

        # call methods
        c = headphones.config.Config(path)
        act1 = c.ALBUM_ART_FORMAT = 'Apple'
        act2 = c.API_ENABLED = True
        act3 = c.API_KEY = 123

        # assertions:
        self.assertEqual(self.config_mock["General"]['album_art_format'], 'Apple')
        self.assertEqual(self.config_mock["General"]['api_enabled'], 1)
        self.assertEqual(self.config_mock["General"]['api_key'], '123')

        self.assertEqual(act1, 'Apple')
        self.assertEqual(act2, 1)

        # TODO : check this strange behaviour. I have expected to see here '123', not 123.
        self.assertEqual(act3, 123)

    # ===========================================================
    #   NEWZNABS
    #

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
        ([1, 2, 3, 'Aaa', 'Bbba', 'Ccccc', 'Ddddda'], [(1, 2, 3), ('Aaa', 'Bbba', 'Ccccc')]),
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

    # ===========================================================
    #   TORZNABS
    # TODO : here is copypaste from of NEZNABS tests. Make tests better, plz refactor them
    #
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
        ([1, 2, 3, 'Aaa', 'Bbba', 'Ccccc', 'Ddddda'], [(1, 2, 3), ('Aaa', 'Bbba', 'Ccccc')]),
    )
    def test_get_extra_torznabs(self, conf_value, expected):
        """ Config: get_extra_torznabs """
        path = '/tmp/notexist'

        #itertools.izip(*[itertools.islice('', i, None, 3) for i in range(3)])
        # set up mocks:
        # 'EXTRA_TORZNABS': (list, '', ''),
        self.config_mock["Torznab"] = {"extra_torznabs": conf_value}

        # call methods
        c = headphones.config.Config(path)
        res = c.get_extra_torznabs()

        # assertions:
        self.assertEqual(res, expected)
