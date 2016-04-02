from unittestcompat import TestCase, TestArgs

from headphones.exceptions import ConfigError
from headphones.config.typeconv import boolext, path
from _datamodel import OptionModel


class OptionModelTest(TestCase):

    # ---------------------------------------------------------------
    # __init__
    # ---------------------------------------------------------------
    def test_init(self):
        """ OptionModel: __init__ """
        p = OptionModel('KEY', 'GeneralSection', 0, int)
        st = {}
        p.bindToConfig(lambda: st)

        self.assertIsNotNone(p)
        self.assertIsInstance(p, OptionModel)

    # ---------------------------------------------------------------
    # get
    # ---------------------------------------------------------------
    @TestArgs(
        (1, int),
    )
    def test_get_without_binding_raises(self, deflt, tp):
        """ OptionModel:get without bindToConfig SHOULD raise """
        p = OptionModel('ANYKEY', 'AnySection', deflt, tp)

        with self.assertRaisesRegexp(ConfigError, r'ANYKEY.*not\sbinded'):
            p.get()

    @TestArgs(
        (1, int),
        (100, int),
        (0, int),
        ('', str),
        ('asdf', str),
        (True, bool),
    )
    def test_get_default(self, deflt, tp):
        """ OptionModel: test get of default value """
        p = OptionModel('KEY', 'GeneralSection', deflt, tp)
        st = {}
        p.bindToConfig(lambda: st)

        act = p.get()
        self.assertIsInstance(act, tp)
        self.assertEqual(act, deflt)

    @TestArgs(
        (1, int, 1, int),
        ("1", int, 1, int),
        ("100", int, 100, int),

        ("1", boolext, True, bool),
        ("on", boolext, True, bool),

        ("/tmp/", path, '/tmp/', path),

        ("hello", str, "hello", str),
    )
    def test_get_default_with_conv(self, deflt, conv, expval, exptp):
        """ OptionModel: test get of default value vith type conversion """
        p = OptionModel('KEY', 'GeneralSection', deflt, conv)
        st = {}
        p.bindToConfig(lambda: st)

        act = p.get()
        self.assertIsInstance(act, exptp)
        self.assertEqual(act, expval)

    @TestArgs(
        (1023, int, 'not an int'),
        ([1023], list, 1),
    )
    def test_get_wrong_type_falls_back_to_default(self, deflt, conv, confval):
        """ OptionModel: get with wrong type in config SHOULD fallback to default """
        sec = 'AnySection'
        key = 'ANYKEY'
        inikey = key.lower()
        p = OptionModel(key, sec, deflt, conv)
        st = {
            sec: {
                inikey: confval
            }
        }
        p.bindToConfig(lambda: st)

        act = p.get()
        self.assertEqual(act, deflt)

    # ---------------------------------------------------------------
    # set
    # ---------------------------------------------------------------
    @TestArgs(
        (1, int),
    )
    def test_set_without_binding_raises(self, deflt, tp):
        """ OptionModel:set without bindToConfig SHOULD raise """
        p = OptionModel('ANYKEY', 'AnySection', deflt, tp)

        with self.assertRaisesRegexp(ConfigError, r'ANYKEY.*not\sbinded'):
            p.set(deflt)

    # ---------------------------------------------------------------
    # section
    # ---------------------------------------------------------------
    @TestArgs(
        ("sec"),
        ("123"),
        ("GEnerAL"),
    )
    def test_section_set_none_to_any(self, new_sec_name):
        """ OptionModel:section:set set value from None to any """

        section_name = None
        p = OptionModel('KEY', section_name, 0, int)

        p.section = new_sec_name

        self.assertEqual(p.section, new_sec_name)

    @TestArgs(
        ("sec", "asdf"),
        ("123", None),
        ("GEnerAL", "Gen"),
    )
    def test_section_set_raise(self, sec1, sec2):
        """ OptionModel:section:set change section should raise """

        p = OptionModel('KEY', sec1, 0, int)

        with self.assertRaisesRegexp(ValueError, r'already set'):
            p.section = sec2

    @TestArgs(
        ("sec", "sec"),
        ("123", "123"),
        ("GEnerAL", "General"),
        ("Web UI", "web ui"),
    )
    def test_section_set(self, sec1, sec2):
        """ OptionModel:section:set change case of value should work """

        p = OptionModel('KEY', sec1, 0, int)

        p.section = sec2
        self.assertEqual(p.section, sec2)
