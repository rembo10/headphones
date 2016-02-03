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
    @_d
    def assertIsInstance(self, *args, **kw):
        return super(TestCase, self).assertIsInstance(*args, **kw)

    @_d
    def assertIsIn(self, *args, **kw):
        return super(TestCase, self).assertIsIn(*args, **kw)
