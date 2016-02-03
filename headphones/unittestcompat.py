import sys
from unittest import TestCase as TC

def _is26():
    if sys.version_info[0] == 2 and sys.version_info[1] == 6:
        return True
    return False

_dummy = _is26()

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

    def assertIsNotNone(self, val, msg=None):
        if not _dummy:
            return super(TestCase, self).assertIsNotNone(val, msg)
        tst = val is not None
        return super(TestCase, self).assertTrue(val, msg)

    class _TestCaseRaiseStub:
        def __init__(self, exc, tc):
            self.exc = exc
            self.tc = tc
        def __enter__(self):
            return self
        def __exit__(self, tp, value, traceback):
            tst = tp is self.exc
            self.tc.assertTrue(tst)
            self.exception = value
            return True

    def assertRaises(self, exc, msg = None):
        if not _dummy:
            return super(TestCase, self).assertRaises(exc, msg)
        return TestCase._TestCaseRaiseStub(exc, self)

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
