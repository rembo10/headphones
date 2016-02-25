import sys
if sys.version_info < (2, 7):
    import unittest2 as unittest
    from unittest2 import TestCase as TC
else:
    import unittest
    from unittest import TestCase as TC

skip = unittest.skip

_dummy = False

# less than 2.6 ...
if sys.version_info[0] == 2 and sys.version_info[1] <= 6:
    _dummy = True


def _d(f):
    def decorate(self, *args, **kw):
        if not _dummy:
            return f(self, *args, **kw)
        return self.assertTrue(True)
    return decorate


class TestCase(TC):
    """
    Wrapper for python 2.6 stubs
    """

    def assertIsInstance(self, obj, cls, msg=None):
        if not _dummy:
            return super(TestCase, self).assertIsInstance(obj, cls, msg)
        tst = isinstance(obj, cls)
        return self.assertTrue(tst, msg)

    @_d
    def assertNotIsInstance(self, *args, **kw):
        return super(TestCase, self).assertNotIsInstance(*args, **kw)

    @_d
    def assertIn(self, *args, **kw):
        return super(TestCase, self).assertIn(*args, **kw)

    @_d
    def assertRegexpMatches(self, *args, **kw):
        return super(TestCase, self).assertRegexpMatches(*args, **kw)

    # -----------------------------------------------------------
    # NOT DUMMY ASSERTIONS
    # -----------------------------------------------------------
    def assertIsNone(self, val, msg=None):
        if not _dummy:
            return super(TestCase, self).assertIsNone(val, msg)
        tst = val is None
        return super(TestCase, self).assertTrue(tst, msg)

    def assertIsNotNone(self, val, msg=None):
        if not _dummy:
            return super(TestCase, self).assertIsNotNone(val, msg)
        tst = val is not None
        return super(TestCase, self).assertTrue(tst, msg)

    def assertRaises(self, exc, msg=None):
        if not _dummy:
            return super(TestCase, self).assertRaises(exc, msg)
        return TestCase._TestCaseRaiseStub(self, exc, msg=msg)

    def assertRaisesRegexp(self, exc, regex, msg=None):
        if not _dummy:
            return super(TestCase, self).assertRaises(exc, msg)
        return TestCase._TestCaseRaiseStub(self, exc, regex=regex, msg=msg)

    class _TestCaseRaiseStub:
        """ Internal stuff for stubbing `assertRaises*` """

        def __init__(self, test_case, exc, regex=None, msg=None):
            self.exc = exc
            self.test_case = test_case
            self.regex = regex
            self.msg = msg

        def __enter__(self):
            return self

        def __exit__(self, tp, value, traceback):
            tst = tp is self.exc
            self.test_case.assertTrue(tst, msg=self.msg)
            self.exception = value

            # TODO: implement self.regex checking

            # True indicates, that exception is handled
            return True


def TestArgs(*parameters):
    def tuplify(x):
        if not isinstance(x, tuple):
            return (x,)
        return x

    def decorator(method, parameters=parameters):
        for parameter in (tuplify(x) for x in parameters):

            def method_for_parameter(self, method=method, parameter=parameter):
                method(self, *parameter)
            args_for_parameter = ",".join(repr(v) for v in parameter)
            name_for_parameter = method.__name__ + "(" + args_for_parameter + ")"
            frame = sys._getframe(1)    # pylint: disable-msg=W0212
            frame.f_locals[name_for_parameter] = method_for_parameter
            frame.f_locals[name_for_parameter].__doc__ = method.__doc__ + '(' + args_for_parameter + ')'
            method_for_parameter.__name__ = name_for_parameter + '(' + args_for_parameter + ')'
        return None
    return decorator
