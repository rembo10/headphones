import mock
from mock import MagicMock
from unittestcompat import TestCase, TestArgs

from headphones.config._meta import MetaConfig


class MetaConfigTest(TestCase):

    def setUp(self):
        self.path = '/tmp/cf.meta.ini'

        self.config_module_mock_patcher = mock.patch('headphones.config._meta.ConfigObj', name='ConfigObjModuleMock')
        self.config_module_mock = self.config_module_mock_patcher.start()

    def tearDown(self):
        self.config_module_mock_patcher.stop()

    @TestArgs(
        (None, True, False),
        ('', True, False),

        ('readonly', True, True),
        ('ro', True, True),
        ('rw', True, False),

        ('show', True, False),
        ('Visible', True, False),
        ('hide', False, False),
        ('hiddeN', False, False),

        ('hIDe, ro', False, True),
        ('RO,hide', False, True),
        ('      ro,    hide ', False, True),

        (',  hidden, rw, ro, hide ', False, True),

        ([u'ro', u'hide'], False, True),
    )
    def test_apply(self, meta_value, exp_visible, exp_readonly):

        self.config_module_mock.return_value = {'section': {'key': meta_value}}

        option = MagicMock()
        option.model.section = 'section'
        option.model.inikey = 'key'

        mc = MetaConfig(self.path)

        mc.apply(option)

        self.assertEqual(option.readonly, exp_readonly)
        self.assertEqual(option.visible, exp_visible)

    @TestArgs(
        ('ro,,go, mo', True, True),
    )
    def test_apply_on_empty_meta_values(self, meta_value, exp_visible, exp_readonly):
        self.config_module_mock.return_value = {'section': {'key': meta_value}}

        option = MagicMock()
        option.model.section = 'section'
        option.model.inikey = 'key'

        mc = MetaConfig(self.path)

        mock_log = MagicMock()
        with mock.patch('headphones.config._meta.logger', mock_log):
            mc.apply(option)

        self.assertTrue(mock_log.warn.called)
        mock_log.warn.assert_any_call('Syntax error in meta-option definition, [section][key] = []')

        self.assertEqual(option.readonly, exp_readonly)
        self.assertEqual(option.visible, exp_visible)

    @TestArgs(
        ('go', 'go', True, False),
        ('ro,go, mo', 'go', True, True),
        ('ro,11111,go, mo', '11111', True, True),
    )
    def test_apply_on_unknown_meta_values(self, meta_value, err_meta, exp_visible, exp_readonly):
        self.config_module_mock.return_value = {'section': {'key': meta_value}}

        option = MagicMock()
        option.model.section = 'section'
        option.model.inikey = 'key'

        mc = MetaConfig(self.path)

        mock_log = MagicMock()
        with mock.patch('headphones.config._meta.logger', mock_log):
            mc.apply(option)

        self.assertTrue(mock_log.warn.called)
        mock_log.warn.assert_any_call('Unknown value of meta [' + err_meta + '] for option [section][key]')

        self.assertEqual(option.readonly, exp_readonly)
        self.assertEqual(option.visible, exp_visible)
