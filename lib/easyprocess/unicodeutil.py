import logging
import shlex
import sys
import unicodedata

log = logging.getLogger(__name__)

PY3 = sys.version_info[0] >= 3

if PY3:
    string_types = str,
else:
    string_types = basestring,


class EasyProcessUnicodeError(Exception):
    pass


def split_command(cmd):
    '''
     - cmd is string list -> nothing to do
     - cmd is string -> split it using shlex

    :param cmd: string ('ls -l') or list of strings (['ls','-l'])
    :rtype: string list
    '''
    if not isinstance(cmd, string_types):
        # cmd is string list
        pass
    else:
        if not PY3:
            # cmd is string
            # The shlex module currently does not support Unicode input (in
            # 2.x)!
            if isinstance(cmd, unicode):
                try:
                    cmd = unicodedata.normalize(
                        'NFKD', cmd).encode('ascii', 'strict')
                except UnicodeEncodeError:
                    raise EasyProcessUnicodeError('unicode command "%s" can not be processed.' % cmd +
                                                  'Use string list instead of string')
                log.debug('unicode is normalized')
        cmd = shlex.split(cmd)
    return cmd


def uniencode(s):
    if PY3:
        pass
#        s=s.encode()
    else:
        if isinstance(s, unicode):
            s = s.encode('utf-8')
    return s


def unidecode(s):
    if PY3:
        s = s.decode()
    else:
        if isinstance(s, str):
            s = s.decode('utf-8', 'ignore')
    return s
