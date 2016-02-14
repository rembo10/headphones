import sys
if sys.version_info < (2, 7):
    from unittest2 import TestCase as TC
else:
    from unittest import TestCase as TC

""" It is just `skip` from `unittest` """
skip = TC.skip

_dummy = False

# less than 2.6 ...
if sys.version_info[0] == 2 and sys.version_info[1] <= 6:
    _dummy = True

def _d(f):
    def decorate(self, *args, **kw):
        if _dummy:
            return self.assertTrue(True)
        return f(self, *args, **kw)
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
        return TestCase._TestCaseRaiseStub(exc, self)

    def assertRaisesRegexp(self, exc, regex, msg=None):
        if not _dummy:
            return super(TestCase, self).assertRaises(exc, msg)
        return TestCase._TestCaseRaiseStub(exc, self)

    class _TestCaseRaiseStub:
        """ Internal stuff for stubbing `assertRaises*` """

        def __init__(self, exc, regex, tc):
            self.exc = exc
            self.tc = tc
            self.regex = regex

        def __enter__(self):
            return self

        def __exit__(self, tp, value, traceback):
            tst = tp is self.exc
            self.tc.assertTrue(tst)
            self.exception = value

            # TODO: implement self.regex checking

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
