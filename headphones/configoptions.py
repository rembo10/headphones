import re

# translation
def _(x):
    return x


def bool_int(value):
    """
    Casts a config value into a 0 or 1
    """
    if isinstance(value, basestring):
        if value.lower() in ('', '0', 'false', 'f', 'no', 'n', 'off'):
            value = 0
    return int(bool(value))


class path(str):
    """Internal 'marker' type for paths in config."""

    @staticmethod
    def __call__(val):
        return path(val)

    def __new__(cls, *args, **kw):
        hstr = str.__new__(cls, *args, **kw)
        return hstr

    def __repr__(self):
        return 'headphones.config.path(%s)' % self






class OptionBase(object):

    def __init__(self, *args, **qw):
        self.tmp = "OptionString"
        pass

class OptionString(OptionBase):

    def __init__(self, appkey, default=None, maxlength=None):
        super(OptionString, self).__init__(appkey)
        self.appkey = appkey

class OptionNumber(OptionBase):

    def __init__(self, appkey, default=None, maxvalue=None, minvalue=None):
        super(OptionNumber, self).__init__(appkey)
        self.appkey = appkey

class OptionSwitch(OptionBase):

    def __init__(self, appkey, default=None):
        super(OptionSwitch, self).__init__(appkey)
        self.appkey = appkey
