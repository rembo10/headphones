import os
import sys
import random
import mock
import logging
from mock import MagicMock
from unittestcompat import TestCase, TestArgs, skip

import headphones.config

logging.basicConfig(stream=sys.stderr)
logger = logging.getLogger('headphones.config.TEST')
logger.setLevel(logging.INFO)


class ConfigApiTest(TestCase):
    """ Common tests for headphones.Config

    Common tests for headphones.Config This test suite guarantees, that external
    API of the Config class conforms all expectations of other modules.

    HELPERS:
        * self.config_mock - autoinitialized (on setUpt) mock of ConfigObj. By default it
                             has two sections: 'Email' and 'General'
        * self.path - unique name of non-existent file. Placeholder for your config.ini
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

        # get unique name for ini file
        while True:
            self.path = './config.' + str(random.randint(1, 999999999)) + '.ini'
            if not os.path.isfile(self.path):
                break

    def tearDown(self):
        self.config_module_mock_patcher.stop()
        try:
            os.remove(self.path)
        except OSError:
            pass

    def test_constructor(self):
        """ Config : creating """

        cf = headphones.config.Config(self.path)
        self.assertIsInstance(cf, headphones.config.Config)

    def test_write(self):
        """ Config : write BE CAREFUL : this test write files on FS """

        self.config_module_mock_patcher.stop()

        logger.info('Config: write will use path[{0}]'.format(self.path))
        # call methods
        cf = headphones.config.Config(self.path)
        cf.write()

        # IMPORTANT ASSERTS: they check, that options are passed to the low-level ConfigObj
        # with appropriate values and names
        from configobj import ConfigObj
        config_tester = ConfigObj(self.path)

        self.assertTrue('General' in config_tester)
        self.assertTrue('Email' in config_tester)

        self.assertFalse('asdf' in config_tester)

        self.assertTrue('download_dir' in config_tester['General'])
        self.assertTrue('git_path' in config_tester['General'])
        self.assertTrue('blackhole' in config_tester['General'])
        self.assertTrue('open_magnet_links' in config_tester['General'])
        self.assertTrue('interface' in config_tester['General'])
        self.assertTrue('config_version' in config_tester['General'])

        self.assertTrue('email_enabled' in config_tester['Email'])
        self.assertTrue('email_from' in config_tester['Email'])

        self.config_module_mock_patcher.start()

    @skip("process_kwargs should be removed")
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

        self.config_mock["General"] = {name.lower(): value}

        # call methods
        c = headphones.config.Config(self.path)
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

        # call methods
        c = headphones.config.Config(self.path)
        res = c.__getattr__(name)

        # assertions:
        self.assertEqual(res, value)

    def test__getattr__ConfValuesDefaultUsingDotNotation(self):
        """ Config: __getattr__ from config (by dot), default values """

        # call methods
        c = headphones.config.Config(self.path)

        # assertions:
        self.assertEqual(c.ALBUM_ART_FORMAT, 'folder')
        self.assertEqual(c.API_ENABLED, 0)
        self.assertEqual(c.API_KEY, '')

    def test__getattr__OwnAttributes(self):
        """ Config: __getattr__ access own attrs """

        # call methods
        c = headphones.config.Config(self.path)

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

        # call methods
        c = headphones.config.Config(self.path)
        act = c.__setattr__(name, value)

        # assertions:
        self.assertEqual(self.config_mock["General"][name.lower()], value)
        self.assertEqual(act, value)

    def test__setattr__ExplicitSetUsingDotNotation(self):
        """ Config: __setattr__ with setting values using dot notation """

        # call methods
        c = headphones.config.Config(self.path)
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
        ('ABCDEA', [('A', 'B', True), ('D', 'E', True)]),
        (['ABC', 'DEF'], []),
        ([1], []),
        ([1, 2], []),
        ([1, 2, 3], [(1, 2, True)]),

        ([1, 2, 3, 'Aaa'], [(1, 2, True)]),
        ([1, 2, 3, 'Aaa', 'Bbba'], [(1, 2, True)]),
        ([1, 2, 3, 'Aaa', 'Bbba', 'Ccccc'], [(1, 2, True), ('Aaa', 'Bbba', True)]),
        ([1, 2, 3, 'Aaa', 'Bbba', 'Ccccc', 'Ddddda'], [(1, 2, True), ('Aaa', 'Bbba', True)]),
    )
    def test_get_extra_newznabs(self, conf_value, expected):
        """ Config: get_extra_newznabs """

        #itertools.izip(*[itertools.islice('', i, None, 3) for i in range(3)])
        # set up mocks:
        # 'EXTRA_NEWZNABS': (list, 'Newznab', ''),
        # 'EXTRA_TORZNABS': (list, 'Torznab', ''),
        self.config_mock["Newznab"] = {"extra_newznabs": conf_value}

        # call methods
        c = headphones.config.Config(self.path)
        res = c.get_extra_newznabs()

        # assertions:
        self.assertEqual(res, expected)

    # ===========================================================
    #   TORZNABS
    # TODO : here is copypaste from of NEZNABS tests. Make tests better, plz refactor them
    #
    @TestArgs(
        ('', []),
        ('ABCDEX', [('A', 'B', True), ('D', 'E', True)]),
        (['ABC', 'DEF'], []),
        ([1], []),
        ([1, 2], []),
        ([1, 2, 3], [(1, 2, True)]),

        ([1, 2, 3, 'Aaa'], [(1, 2, True)]),
        ([1, 2, 3, 'Aaa', 'Bbba'], [(1, 2, True)]),
        ([1, 2, 3, 'Aaa', 'Bbba', 'Ccccc'], [(1, 2, True), ('Aaa', 'Bbba', True)]),
        ([1, 2, 3, 'Aaa', 'Bbba', 'Ccccc', 'Ddddda'], [(1, 2, True), ('Aaa', 'Bbba', True)]),
    )
    def test_get_extra_torznabs(self, conf_value, expected):
        """ Config: get_extra_torznabs """

        #itertools.izip(*[itertools.islice('', i, None, 3) for i in range(3)])
        # set up mocks:
        # 'EXTRA_TORZNABS': (list, '', ''),
        self.config_mock["Torznab"] = {"extra_torznabs": conf_value}

        # call methods
        c = headphones.config.Config(self.path)
        res = c.get_extra_torznabs()

        # assertions:
        self.assertEqual(res, expected)
