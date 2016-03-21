from headphones import logger
from headphones.exceptions import ConfigError

""" List of types, which ConfigOpt could handle internally, without conversions """
_primitives = (int, str, bool, list, float)


class OptionModel(object):
    """ Stores value of option, and know, how to write this value to the config file"""

    def __init__(self, appkey, section, default, initype):

        self._config_callback = None

        self._appkey = appkey
        self._inikey = appkey.lower()
        self._section = section
        self._default = default
        self._initype = initype

    def _exists(self):
        c = self._config_callback()
        return (self._section in c) and (self._inikey in c[self._section])

    @property
    def appkey(self):
        return self._appkey

    @property
    def inikey(self):
        return self._inikey

    @property
    def section(self):
        return self._section

    @section.setter
    def section(self, value):
        """ The value of 'section' is immutable. But it is possible to change CASE of this value """
        ov = self._section.lower() if self._section else None
        nv = value.lower() if value else None

        # is immutable. Could change case of chars, or change value from None to not None
        if (ov is None) or (ov == nv):
            self._section = value
        else:
            raise ValueError('section already set')
        return self._section

    def bindToConfig(self, config_callback):
        self._config_callback = config_callback
        if not self._exists():
            self.set(self._default)

    def get(self):
        # abbreviation. I am too lazy to write 'self._inikey', will use 'k'
        s = self._section   # section
        k = self._inikey    # key
        t = self._initype   # type
        d = self._default

        if self._config_callback is None:
            msg = 'Option [{0}][{1}] was not binded to config'.format(s, k)
            logger.error(msg)
            raise ConfigError(msg)

        if not self._exists():
            msg = 'Option [{0}][{1}] does not exist in config'.format(s, k)
            logger.error(msg)
            raise ConfigError(msg)

        config = self._config_callback()
        v = config[s][k]
        # cast to target type IF REQUIRED. do not convert, if variable is already of target type
        if not isinstance(t, type) or not isinstance(v, t):
            try:
                v = t(v)
            except TypeError:
                logger.error('The value of option [{0}][{1}] is not well-typed. Will try to use default value.'.format(s, k))
                v = d if isinstance(t, type) and isinstance(d, t) else t(d)
            except ValueError:
                logger.error('The value of option [{0}][{1}] is not well-typed. Will try to use default value.'.format(s, k))
                v = d if isinstance(t, type) and isinstance(d, t) else t(d)

        return v

    def set(self, value):
        # abbreviation. I am too lazy to write 'self._inikey', will use 'k'
        s = self._section   # section
        k = self._inikey    # key
        t = self._initype   # type

        if self._config_callback is None:
            msg = 'Option [{0}][{1}] was not binded/registered with config'.format(s, k)
            logger.error(msg)
            raise ConfigError(msg)

        config = self._config_callback()

        if s not in config:
            # create section:
            logger.debug('Section [{0}] for option [{0}][{1}] doesn\'t exists in config. Create empty.'.format(s, k))
            config[s] = {}

        if k not in config[s]:
            # debug about new config value:
            logger.debug('Option [{0}][{1}] doesn\'t exists in config. Set to default.'.format(s, k))

        # convert value to storable types:
        if not isinstance(value, _primitives):
            logger.debug('Value of option [{0}][{1}] is not primitive [{2}], will `str` it'.format(s, k, type(value)))
            value = str(value)
        else:
            value = t(value)

        config[s][k] = value
