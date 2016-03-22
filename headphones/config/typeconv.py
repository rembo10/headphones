def boolext(value):
    """ extended bool could read bool values from strings like '0', 'f', 'no' ano others.
    """
    if isinstance(value, basestring):
        v = value.lower()
        if v in ('', '0', 'false', 'f', 'no', 'n', 'off', '-'):
            return False
        if v in ('1', 'true', 't', 'yes', 'y', 'on', '+'):
            return True
    return bool(value)


def floatnullable(value):
    """ Nullable float. Works good for empty strings ( "" => None )
    """
    if value is None:
        return None

    # check for empty STRING:
    if isinstance(value, basestring) and not value.strip():
        return None

    return float(value)


def intnullable(value):
    """ Nullable int. Works good for empty strings ( "" => None )
    """
    if value is None:
        return None

    # check for empty STRING:
    if isinstance(value, basestring) and not value.strip():
        return None

    return int(value)


class path(str):
    """ path-type for option value

    Describes the path on the file system.
    """

    @staticmethod
    def __call__(val):
        return path(val)

    def __new__(cls, *args, **kw):
        hstr = str.__new__(cls, *args, **kw)
        return hstr

    def __repr__(self):
        return 'headphones.config.types.path(%s)' % self
